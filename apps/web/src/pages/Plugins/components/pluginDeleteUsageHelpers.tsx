import { Space, Typography } from 'antd';

import type {
  PluginActionRecord,
  PluginConnectionRecord,
  PluginRecord,
  ScheduledJobRecord,
} from '../../../services/aiBrain';

export type DeleteUsageGroup = {
  items: string[];
  label: string;
};

type UsageItem = {
  code?: string;
  id?: string;
  name?: string | null;
};

export function usageItemName(item: UsageItem) {
  return item.name || item.code || item.id || '-';
}

export function hasDeleteUsage(groups: DeleteUsageGroup[]) {
  return groups.some((group) => group.items.length > 0);
}

export function deleteUsageContent(groups: DeleteUsageGroup[]) {
  return (
    <Space orientation="vertical" size={8}>
      <Typography.Text>当前对象正在被使用，不能删除。请先解除下面的引用，或将其停用。</Typography.Text>
      {groups.filter((group) => group.items.length > 0).map((group) => (
        <div key={group.label}>
          <Typography.Text strong>{group.label}：</Typography.Text>
          <Typography.Text>{group.items.slice(0, 5).join('、')}</Typography.Text>
          {group.items.length > 5 ? <Typography.Text type="secondary"> 等 {group.items.length} 个</Typography.Text> : null}
        </div>
      ))}
    </Space>
  );
}

function idSet(singleId?: string | null, ids?: string[]) {
  const values = new Set<string>();
  if (singleId) {
    values.add(String(singleId));
  }
  for (const id of ids ?? []) {
    if (id) {
      values.add(String(id));
    }
  }
  return values;
}

function scheduledJobUsesAnyId(ids: Set<string>, jobIds: Set<string>) {
  for (const id of ids) {
    if (jobIds.has(id)) {
      return true;
    }
  }
  return false;
}

function scheduledJobUsesConnection(job: ScheduledJobRecord, connectionId: string) {
  return idSet(job.plugin_connection_id, job.plugin_connection_ids).has(connectionId);
}

function scheduledJobUsesAction(job: ScheduledJobRecord, actionId: string) {
  return idSet(job.plugin_action_id, job.plugin_action_ids).has(actionId);
}

export function pluginDeleteUsageGroups({
  actions,
  connections,
  plugin,
  scheduledJobs,
}: {
  actions: PluginActionRecord[];
  connections: PluginConnectionRecord[];
  plugin: PluginRecord;
  scheduledJobs: ScheduledJobRecord[];
}): DeleteUsageGroup[] {
  const pluginConnections = connections.filter((connection) => connection.plugin_id === plugin.id);
  const pluginActions = actions.filter((action) => action.plugin_id === plugin.id);
  const connectionIds = new Set(pluginConnections.map((connection) => connection.id));
  const actionIds = new Set(pluginActions.map((action) => action.id));
  return [
    { items: pluginConnections.map(usageItemName), label: '连接' },
    { items: pluginActions.map(usageItemName), label: '动作' },
    {
      items: scheduledJobs
        .filter((job) => (
          scheduledJobUsesAnyId(actionIds, idSet(job.plugin_action_id, job.plugin_action_ids))
          || scheduledJobUsesAnyId(connectionIds, idSet(job.plugin_connection_id, job.plugin_connection_ids))
        ))
        .map(usageItemName),
      label: '定时作业',
    },
  ];
}

export function connectionDeleteUsageGroups({
  actions,
  connection,
  scheduledJobs,
}: {
  actions: PluginActionRecord[];
  connection: PluginConnectionRecord;
  scheduledJobs: ScheduledJobRecord[];
}): DeleteUsageGroup[] {
  return [
    {
      items: actions
        .filter((action) => action.connection_id === connection.id)
        .map(usageItemName),
      label: '动作',
    },
    {
      items: scheduledJobs
        .filter((job) => scheduledJobUsesConnection(job, connection.id))
        .map(usageItemName),
      label: '定时作业',
    },
  ];
}

export function actionDeleteUsageGroups({
  action,
  scheduledJobs,
}: {
  action: PluginActionRecord;
  scheduledJobs: ScheduledJobRecord[];
}): DeleteUsageGroup[] {
  return [
    {
      items: scheduledJobs
        .filter((job) => scheduledJobUsesAction(job, action.id))
        .map(usageItemName),
      label: '定时作业',
    },
  ];
}
