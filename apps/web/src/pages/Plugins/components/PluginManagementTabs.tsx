import { Tabs } from 'antd';

import type {
  AiExecutorRunnerListQuery,
  AiExecutorRunnerRecord,
  PluginActionListQuery,
  PluginActionRecord,
  PluginConnectionListQuery,
  PluginConnectionRecord,
  PluginMarketplaceItem,
  PluginRecord,
} from '../../../services/aiBrain';
import { PluginActionTable } from './PluginActionTable';
import { PluginConnectionTable } from './PluginConnectionTable';
import { PluginMarketplaceTable } from './PluginMarketplaceTable';
import { PluginRunnerTable } from './PluginRunnerTable';
import { PluginTable } from './PluginTable';

type PluginManagementTabsProps = {
  actions: PluginActionRecord[];
  actionListMeta: {
    page: number;
    pageSize: number;
    total: number;
  };
  connectionById: Map<string, PluginConnectionRecord>;
  connectionListMeta: {
    page: number;
    pageSize: number;
    total: number;
  };
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
  onActionListChange: (query: PluginActionListQuery) => void;
  onConnectionListChange: (query: PluginConnectionListQuery) => void;
  onEditAction: (action: PluginActionRecord) => void;
  onEditConnection: (connection: PluginConnectionRecord) => void;
  onEditPlugin: (plugin: PluginRecord) => void;
  onEditRunner: (runner: AiExecutorRunnerRecord) => void;
  onOpenRunnerLogs: (runner: AiExecutorRunnerRecord) => void;
  onReload: () => void;
  onRotateRunnerToken: (runner: AiExecutorRunnerRecord) => void;
  onRunAction: (action: PluginActionRecord) => void;
  onTestConnection: (connection: PluginConnectionRecord) => void;
  onTestRunner: (runner: AiExecutorRunnerRecord) => void;
  onTrialAction: (action: PluginActionRecord) => void;
  pluginById: Map<string, PluginRecord>;
  plugins: PluginRecord[];
  runnerListMeta: {
    page: number;
    pageSize: number;
    performance?: {
      duration_ms?: number;
    };
    total: number;
  };
  runners: AiExecutorRunnerRecord[];
  onRunnerListChange: (query: AiExecutorRunnerListQuery) => void;
  testingConnectionId?: string;
  testingRunnerId?: string;
};

export function PluginManagementTabs({
  actions,
  actionListMeta,
  connectionById,
  connectionListMeta,
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
  onActionListChange,
  onConnectionListChange,
  onEditAction,
  onEditConnection,
  onEditPlugin,
  onEditRunner,
  onOpenRunnerLogs,
  onReload,
  onRotateRunnerToken,
  onRunAction,
  onTestConnection,
  onTestRunner,
  onTrialAction,
  pluginById,
  plugins,
  runnerListMeta,
  runners,
  onRunnerListChange,
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
              loading={loading}
              pluginById={pluginById}
              remote={connectionListMeta}
              testingConnectionId={testingConnectionId}
              onCreateConnection={onCreateConnection}
              onDeleteConnection={onDeleteConnection}
              onEditConnection={onEditConnection}
              onRemoteChange={onConnectionListChange}
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
              remote={runnerListMeta}
              runners={runners}
              testingRunnerId={testingRunnerId}
              onCopySetupCommand={onCopyRunnerSetupCommand}
              onCreateRunner={onCreateRunner}
              onDeleteRunner={onDeleteRunner}
              onDownloadInstallPackage={onDownloadRunnerInstallPackage}
              onEditRunner={onEditRunner}
              onOpenLogs={onOpenRunnerLogs}
              onRemoteChange={onRunnerListChange}
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
              remote={actionListMeta}
              onCreateAction={onCreateAction}
              onDeleteAction={onDeleteAction}
              onEditAction={onEditAction}
              onRemoteChange={onActionListChange}
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
