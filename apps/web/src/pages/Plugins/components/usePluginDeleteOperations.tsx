import { Modal, message } from 'antd';
import { useCallback } from 'react';

import {
  deletePlugin,
  deletePluginAction,
  deletePluginConnection,
  type PluginActionRecord,
  type PluginConnectionRecord,
  type PluginRecord,
  type ScheduledJobRecord,
} from '../../../services/aiBrain';
import {
  actionDeleteUsageGroups,
  connectionDeleteUsageGroups,
  deleteUsageContent,
  hasDeleteUsage,
  pluginDeleteUsageGroups,
} from './pluginDeleteUsageHelpers';

export function usePluginDeleteOperations({
  actions,
  connections,
  reload,
  scheduledJobs,
}: {
  actions: PluginActionRecord[];
  connections: PluginConnectionRecord[];
  reload: () => Promise<void>;
  scheduledJobs: ScheduledJobRecord[];
}) {
  const warnDeleteUsage = useCallback((title: string, groups: ReturnType<typeof pluginDeleteUsageGroups>) => {
    Modal.warning({
      content: deleteUsageContent(groups),
      okText: '知道了',
      title,
      width: 640,
    });
  }, []);

  const confirmDeletePlugin = useCallback((plugin: PluginRecord) => {
    if (plugin.is_system) {
      message.info('官方标准插件不能删除，请在连接里维护接入参数');
      return;
    }
    const usageGroups = pluginDeleteUsageGroups({ actions, connections, plugin, scheduledJobs });
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`插件「${plugin.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除插件「${plugin.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除插件',
      onOk: async () => {
        try {
          await deletePlugin(plugin.id);
          message.success('插件已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '插件删除失败');
        }
      },
    });
  }, [actions, connections, reload, scheduledJobs, warnDeleteUsage]);

  const confirmDeleteConnection = useCallback((connection: PluginConnectionRecord) => {
    const usageGroups = connectionDeleteUsageGroups({ actions, connection, scheduledJobs });
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`连接「${connection.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除连接「${connection.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除连接',
      onOk: async () => {
        try {
          await deletePluginConnection(connection.id);
          message.success('连接已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '连接删除失败');
        }
      },
    });
  }, [actions, reload, scheduledJobs, warnDeleteUsage]);

  const confirmDeleteAction = useCallback((action: PluginActionRecord) => {
    const usageGroups = actionDeleteUsageGroups({ action, scheduledJobs });
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`动作「${action.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除动作「${action.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除动作',
      onOk: async () => {
        try {
          await deletePluginAction(action.id);
          message.success('动作已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '动作删除失败');
        }
      },
    });
  }, [reload, scheduledJobs, warnDeleteUsage]);

  return {
    confirmDeleteAction,
    confirmDeleteConnection,
    confirmDeletePlugin,
  };
}
